package com.talentlens.service.impl;

import com.talentlens.dto.request.LoginRequest;
import com.talentlens.dto.request.RefreshTokenRequest;
import com.talentlens.dto.request.RegisterRequest;
import com.talentlens.dto.response.AuthResponse;
import com.talentlens.dto.response.UserResponse;
import com.talentlens.exception.DuplicateResourceException;
import com.talentlens.exception.ResourceNotFoundException;
import com.talentlens.exception.UnauthorizedException;
import com.talentlens.mapper.UserMapper;
import com.talentlens.model.User;
import com.talentlens.repository.UserRepository;
import com.talentlens.security.JwtTokenProvider;
import com.talentlens.service.AuthService;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import java.time.Instant;

@Service
@RequiredArgsConstructor
public class AuthServiceImpl implements AuthService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtTokenProvider jwtTokenProvider;
    private final UserMapper userMapper;

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

        if (!passwordEncoder.matches(request.getPassword(), user.getPassword())) {
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
}
