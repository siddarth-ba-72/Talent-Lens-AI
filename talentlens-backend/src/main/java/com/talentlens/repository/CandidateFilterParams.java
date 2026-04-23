package com.talentlens.repository;

import lombok.Builder;
import lombok.Data;

import java.util.List;

@Data
@Builder
public class CandidateFilterParams {
    private List<String> skills;
    private String source;
    private Integer minScore;
    private Integer maxScore;
    private String keyword;
}
