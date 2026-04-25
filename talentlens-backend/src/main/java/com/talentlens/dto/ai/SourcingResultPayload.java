package com.talentlens.dto.ai;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class SourcingResultPayload {
    private String taskId;
    private String searchId;
    private String runId;
    private String status;
    private int candidatesFound;
    private List<SourcedCandidatePayload> candidates;
    private String error;
    private Instant completedAt;
}
