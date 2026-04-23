package com.talentlens.dto.response;

import java.util.List;

public record ParsedJdDto(
        List<String> skills,
        List<String> responsibilities,
        String experienceLevel,
        List<String> qualifications,
        List<String> technologies,
        String domain,
        String summary
) {}
