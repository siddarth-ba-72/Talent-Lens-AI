package com.talentlens.dto.ai;

import com.talentlens.model.embedded.ScoreBreakdown;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class SourcedCandidatePayload {
    private String name;
    private String email;
    private String avatarUrl;
    private String profileUrl;
    private String source;
    private String sourceUsername;
    private List<String> skills;
    private String bio;
    private String location;
    private String experience;
    private int matchScore;
    private ScoreBreakdown scoreBreakdown;
    private Instant sourcedAt;
}
