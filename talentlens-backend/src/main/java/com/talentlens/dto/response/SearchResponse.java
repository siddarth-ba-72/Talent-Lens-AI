package com.talentlens.dto.response;

import java.time.Instant;
import java.util.List;

public record SearchResponse(
        String id,
        String title,
        String rawJdText,
        String jdFileName,
        ParsedJdDto parsedJd,
        String sourcingStatus,
        List<String> sourcingPlatforms,
        int candidateCount,
        List<String> sharedWith,
        Instant createdAt,
        Instant updatedAt
) {}
