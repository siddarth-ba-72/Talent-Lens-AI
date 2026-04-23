package com.talentlens.dto.response;

public record ScoreBreakdownDto(
        int skillMatch,
        int experienceMatch,
        int overallFit
) {}
