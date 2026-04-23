package com.talentlens.model;

import com.talentlens.model.embedded.ScoreBreakdown;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.CompoundIndex;
import org.springframework.data.mongodb.core.index.CompoundIndexes;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;
import java.util.List;

@Document(collection = "candidates")
@CompoundIndexes({
    @CompoundIndex(def = "{'searchId': 1, 'runId': 1, 'source': 1, 'sourceUsername': 1}", unique = true),
    @CompoundIndex(def = "{'searchId': 1, 'isActive': 1, 'matchScore': -1}")
})
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Candidate {

    @Id
    private String id;

    private String searchId;
    private String runId;
    private String name;
    private String email;
    private String avatarUrl;
    private String profileUrl;
    private CandidateSource source;
    private String sourceUsername;
    private List<String> skills;
    private String bio;
    private String location;
    private String experience;
    private int matchScore;
    private ScoreBreakdown scoreBreakdown;
    private boolean isActive;
    private Instant sourcedAt;
    private Instant createdAt;
}
