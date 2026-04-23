package com.talentlens.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.annotation.Order;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.time.Instant;
import java.util.concurrent.ConcurrentHashMap;

@Component
@Order(1)
@Slf4j
public class RateLimitFilter extends OncePerRequestFilter {

    private static final String[] PROTECTED_PATHS = {"/api/auth/login", "/api/auth/register"};

    @Value("${app.rate-limit.max-attempts}")
    private int maxAttempts;

    @Value("${app.rate-limit.window-seconds}")
    private long windowSeconds;

    private final ConcurrentHashMap<String, AttemptRecord> attempts = new ConcurrentHashMap<>();

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {
        if (isProtectedPath(request.getRequestURI())) {
            String clientIp = resolveClientIp(request);
            if (isRateLimited(clientIp)) {
                log.warn("Rate limit exceeded for IP: {}", clientIp);
                response.setStatus(HttpStatus.TOO_MANY_REQUESTS.value());
                response.setHeader("Retry-After", String.valueOf(windowSeconds));
                response.getWriter().write("{\"error\":\"TOO_MANY_REQUESTS\",\"message\":\"Too many attempts. Please try again later.\"}");
                return;
            }
        }
        filterChain.doFilter(request, response);
    }

    private boolean isProtectedPath(String uri) {
        for (String path : PROTECTED_PATHS) {
            if (uri.equals(path)) return true;
        }
        return false;
    }

    private boolean isRateLimited(String clientIp) {
        Instant now = Instant.now();
        AttemptRecord record = attempts.compute(clientIp, (ip, existing) -> {
            if (existing == null || now.isAfter(existing.windowStart().plusSeconds(windowSeconds))) {
                return new AttemptRecord(1, now);
            }
            return new AttemptRecord(existing.count() + 1, existing.windowStart());
        });
        return record.count() > maxAttempts;
    }

    private String resolveClientIp(HttpServletRequest request) {
        String forwarded = request.getHeader("X-Forwarded-For");
        if (forwarded != null && !forwarded.isEmpty()) {
            return forwarded.split(",")[0].trim();
        }
        return request.getRemoteAddr();
    }

    private record AttemptRecord(int count, Instant windowStart) {}
}
