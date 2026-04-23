package com.talentlens.dto.response;

public record UserResponse(
        String id,
        String name,
        String email,
        String role
) {}
