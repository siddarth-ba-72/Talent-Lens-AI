package com.talentlens.service.impl;

import com.talentlens.dto.request.GoogleCallbackRequest;
import com.talentlens.dto.request.GoogleCompleteSignupRequest;
import com.talentlens.dto.request.LoginRequest;
import com.talentlens.dto.request.RefreshTokenRequest;
import com.talentlens.dto.request.RegisterRequest;
import com.talentlens.dto.response.AuthResponse;
import com.talentlens.dto.response.GoogleCallbackResponse;
import com.talentlens.dto.response.UserResponse;
import com.talentlens.exception.DuplicateResourceException;
import com.talentlens.exception.OidcException;
import com.talentlens.exception.ResourceNotFoundException;
import com.talentlens.exception.UnauthorizedException;
import com.talentlens.mapper.UserMapper;
import com.talentlens.model.AuthProvider;
import com.talentlens.model.User;
import com.talentlens.repository.UserRepository;
import com.talentlens.security.JwtTokenProvider;
import com.talentlens.service.AuthService;
import com.talentlens.service.GoogleIdentity;
import com.talentlens.service.GoogleOidcService;
import io.jsonwebtoken.Claims;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.EnumSet;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

@Service
@Slf4j
@RequiredArgsConstructor
public class AuthServiceImpl implements AuthService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtTokenProvider jwtTokenProvider;
    private final UserMapper userMapper;
    private final GoogleOidcService googleOidcService;

    @Override
    public UserResponse register(RegisterRequest request) {
        if (userRepository.existsByEmail(request.getEmail())) {
            throw new DuplicateResourceException("Email already registered: " + request.getEmail());
        }

        User user = User.builder()
                .email(request.getEmail())
                .password(passwordEncoder.encode(request.getPassword()))
                .name(request.getName())
                .role(request.resolveRole())
                .authProviders(EnumSet.of(AuthProvider.LOCAL))
                .emailVerified(false)
                .createdAt(Instant.now())
                .updatedAt(Instant.now())
                .build();

        User saved = userRepository.save(user);
        return userMapper.toResponse(saved);
    }

    @Override
    public AuthResponse login(LoginRequest request) {
        User user = userRepository.findByEmail(request.getEmail())
                .orElseThrow(() -> new UnauthorizedException("Invalid credentials"));

        // Google-only users have no password; reject with the same generic error.
        if (user.getPassword() == null || user.getPassword().isEmpty()
                || !passwordEncoder.matches(request.getPassword(), user.getPassword())) {
            throw new UnauthorizedException("Invalid credentials");
        }

        return new AuthResponse(
                jwtTokenProvider.generateAccessToken(user),
                jwtTokenProvider.generateRefreshToken(user.getId()),
            userMapper.toResponse(user)
        );
    }

    @Override
    public AuthResponse refresh(RefreshTokenRequest request) {
        jwtTokenProvider.validateRefreshToken(request.getRefreshToken());
        String userId = jwtTokenProvider.extractUserId(request.getRefreshToken());

        User user = userRepository.findById(userId)
                .orElseThrow(() -> new UnauthorizedException("User not found"));

        return new AuthResponse(
                jwtTokenProvider.generateAccessToken(user),
                jwtTokenProvider.generateRefreshToken(user.getId()),
            userMapper.toResponse(user)
        );
    }

    @Override
    public UserResponse getProfile(String userId) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new ResourceNotFoundException("User not found"));
        return userMapper.toResponse(user);
    }

    @Override
    public GoogleCallbackResponse googleCallback(GoogleCallbackRequest request) {
        GoogleIdentity identity = googleOidcService.exchangeCodeAndVerify(
                request.getCode(), request.getCodeVerifier(), request.getNonce()
        );

        // 1. Existing Google-linked user
        var byGoogleId = userRepository.findByGoogleId(identity.googleSub());
        if (byGoogleId.isPresent()) {
            return GoogleCallbackResponse.authenticated(buildAuthResponse(byGoogleId.get()));
        }

        // 2. Auto-link by verified email
        var byEmail = userRepository.findByEmail(identity.email());
        if (byEmail.isPresent()) {
            User existing = byEmail.get();
            existing.setGoogleId(identity.googleSub());
            Set<AuthProvider> providers = existing.getAuthProviders() == null
                    ? new HashSet<>() : new HashSet<>(existing.getAuthProviders());
            providers.add(AuthProvider.GOOGLE);
            existing.setAuthProviders(providers);
            existing.setEmailVerified(true);
            if (existing.getAvatarUrl() == null && identity.picture() != null) {
                existing.setAvatarUrl(identity.picture());
            }
            existing.setUpdatedAt(Instant.now());
            User saved = userRepository.save(existing);
            return GoogleCallbackResponse.authenticated(buildAuthResponse(saved));
        }

        // 3. Brand-new user — issue signup ticket, await role selection
        String ticket = jwtTokenProvider.generateSignupTicket(Map.of(
                "googleSub", identity.googleSub(),
                "email", identity.email(),
                "name", identity.name() == null ? "" : identity.name(),
                "picture", identity.picture() == null ? "" : identity.picture()
        ));
        return GoogleCallbackResponse.needsRoleSelection(ticket, identity.email(), identity.name(), identity.picture());
    }

    @Override
    public AuthResponse googleCompleteSignup(GoogleCompleteSignupRequest request) {
        Claims claims;
        try {
            claims = jwtTokenProvider.validateSignupTicket(request.getSignupTicket());
        } catch (UnauthorizedException ex) {
            throw new OidcException("signup_expired", "Signup ticket invalid or expired");
        }

        String googleSub = claims.get("googleSub", String.class);
        String email = claims.get("email", String.class);
        String name = claims.get("name", String.class);
        String picture = claims.get("picture", String.class);

        if (googleSub == null || email == null) {
            throw new OidcException("signup_invalid", "Signup ticket missing required claims");
        }

        // Race-guard: did someone register this email between callback and complete-signup?
        if (userRepository.existsByEmail(email)) {
            throw new DuplicateResourceException("Email already registered: " + email);
        }

        User user = User.builder()
                .email(email)
                .password(null)
                .name(name == null || name.isBlank() ? email : name)
                .role(request.getRole())
                .googleId(googleSub)
                .authProviders(EnumSet.of(AuthProvider.GOOGLE))
                .emailVerified(true)
                .avatarUrl(picture == null || picture.isBlank() ? null : picture)
                .createdAt(Instant.now())
                .updatedAt(Instant.now())
                .build();

        User saved = userRepository.save(user);
        return buildAuthResponse(saved);
    }

    private AuthResponse buildAuthResponse(User user) {
        return new AuthResponse(
                jwtTokenProvider.generateAccessToken(user),
                jwtTokenProvider.generateRefreshToken(user.getId()),
                userMapper.toResponse(user)
        );
    }
}
