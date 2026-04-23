package com.talentlens.model.embedded;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ScoreBreakdown {
    private int skillMatch;
    private int experienceMatch;
    private int overallFit;
}
