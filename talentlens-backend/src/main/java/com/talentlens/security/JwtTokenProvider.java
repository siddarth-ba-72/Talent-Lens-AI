package com.talentlens.security;

import com.talentlens.exception.UnauthorizedException;
import com.talentlens.model.User;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.ExpiredJwtException;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;

@Component
@Slf4j
public class JwtTokenProvider {

    private static final String CLAIM_ROLE = "role";
    private static final String CLAIM_EMAIL = "email";
    private static final String CLAIM_TYPE = "type";
    private static final String TYPE_REFRESH = "REFRESH";

    @Value("${app.jwt.secret}")
    private String secret;

    @Value("${app.jwt.access-expiry-ms}")
    private long accessExpiryMs;

    @Value("${app.jwt.refresh-expiry-ms}")
    private long refreshExpiryMs;

    private SecretKey signingKey;

    @PostConstruct
    public void init() {
        if (secret.length() < 32) {
            throw new IllegalStateException("JWT secret must be at least 32 characters");
        }
        signingKey = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
    }

    public String generateAccessToken(User user) {
        Date now = new Date();
        return Jwts.builder()
                .subject(user.getId())
                .claim(CLAIM_EMAIL, user.getEmail())
                .claim(CLAIM_ROLE, user.getRole().name())
                .issuedAt(now)
                .expiration(new Date(now.getTime() + accessExpiryMs))
                .signWith(signingKey, Jwts.SIG.HS256)
                .compact();
    }

    public String generateRefreshToken(String userId) {
        Date now = new Date();
        return Jwts.builder()
                .subject(userId)
                .claim(CLAIM_TYPE, TYPE_REFRESH)
                .issuedAt(now)
                .expiration(new Date(now.getTime() + refreshExpiryMs))
                .signWith(signingKey, Jwts.SIG.HS256)
                .compact();
    }

    public Claims validateAndExtractClaims(String token) {
        try {
            return Jwts.parser()
                    .verifyWith(signingKey)
                    .build()
                    .parseSignedClaims(token)
                    .getPayload();
        } catch (ExpiredJwtException ex) {
            throw new UnauthorizedException("Token has expired");
        } catch (JwtException ex) {
            throw new UnauthorizedException("Invalid token");
        }
    }

    public String extractUserId(String token) {
        return validateAndExtractClaims(token).getSubject();
    }

    public String extractRole(String token) {
        return validateAndExtractClaims(token).get(CLAIM_ROLE, String.class);
    }

    public void validateRefreshToken(String token) {
        Claims claims = validateAndExtractClaims(token);
        if (!TYPE_REFRESH.equals(claims.get(CLAIM_TYPE, String.class))) {
            throw new UnauthorizedException("Not a refresh token");
        }
    }
}
