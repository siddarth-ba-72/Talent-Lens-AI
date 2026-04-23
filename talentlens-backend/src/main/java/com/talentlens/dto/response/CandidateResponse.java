package com.talentlens.dto.response;

import java.time.Instant;
import java.util.List;

public record CandidateResponse(
        String id,
        String searchId,
        String runId,
        String name,
        String email,
        String avatarUrl,
        String profileUrl,
        String source,
        String sourceUsername,
        List<String> skills,
        String bio,
        String location,
        int matchScore,
        ScoreBreakdownDto scoreBreakdown,
        Instant sourcedAt
) {}
