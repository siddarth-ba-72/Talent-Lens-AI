package com.talentlens.repository;

import lombok.Builder;
import lombok.Data;

import java.time.Instant;

@Data
@Builder
public class SearchFilterParams {
    private String keyword;
    private String status;
    private Instant dateFrom;
    private Instant dateTo;
}
