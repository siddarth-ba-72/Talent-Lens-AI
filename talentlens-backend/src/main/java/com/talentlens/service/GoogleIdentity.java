package com.talentlens.service;

public record GoogleIdentity(
        String googleSub,
        String email,
        boolean emailVerified,
        String name,
        String picture
) {}
