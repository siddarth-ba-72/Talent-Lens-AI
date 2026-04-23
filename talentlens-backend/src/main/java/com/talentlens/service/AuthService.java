package com.talentlens.service;

import com.talentlens.dto.request.LoginRequest;
import com.talentlens.dto.request.RefreshTokenRequest;
import com.talentlens.dto.request.RegisterRequest;
import com.talentlens.dto.response.AuthResponse;
import com.talentlens.dto.response.UserResponse;

public interface AuthService {
    UserResponse register(RegisterRequest request);
    AuthResponse login(LoginRequest request);
    AuthResponse refresh(RefreshTokenRequest request);
    UserResponse getProfile(String userId);
}
