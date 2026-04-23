package com.talentlens.dto.response;

import java.time.Instant;
import java.util.List;

public record SearchSummaryResponse(
        String id,
        String title,
        String sourcingStatus,
        List<String> sourcingPlatforms,
        int candidateCount,
        Instant createdAt
) {}
