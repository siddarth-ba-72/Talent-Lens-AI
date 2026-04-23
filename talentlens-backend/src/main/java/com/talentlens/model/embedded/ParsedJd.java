package com.talentlens.model.embedded;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ParsedJd {
    private List<String> skills;
    private List<String> responsibilities;
    private String experienceLevel;
    private List<String> qualifications;
    private List<String> technologies;
    private String domain;
    private String summary;
}
