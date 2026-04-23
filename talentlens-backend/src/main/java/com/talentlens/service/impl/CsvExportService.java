package com.talentlens.service.impl;

import com.talentlens.exception.ResourceNotFoundException;
import com.talentlens.model.Candidate;
import com.talentlens.repository.CandidateFilterParams;
import com.talentlens.repository.CandidateRepository;
import com.talentlens.repository.SearchRepository;
import com.talentlens.service.ExportService;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.io.PrintWriter;
import java.util.List;
import java.util.stream.Collectors;

@Service("csv")
@RequiredArgsConstructor
@Slf4j
public class CsvExportService implements ExportService {

    private final CandidateRepository candidateRepository;
    private final SearchRepository searchRepository;

    @Override
    public String format() {
        return "csv";
    }

    @Override
    public void export(String searchId, CandidateFilterParams params, HttpServletResponse response) {
        if (!searchRepository.existsById(searchId)) {
            throw new ResourceNotFoundException("Search not found: " + searchId);
        }

        List<Candidate> candidates = candidateRepository.findAllWithFilters(searchId, params);

        response.setContentType("text/csv");
        response.setHeader("Content-Disposition", "attachment; filename=\"candidates-" + searchId + ".csv\"");

        try (PrintWriter writer = response.getWriter()) {
            writer.println("id,name,email,source,sourceUsername,profileUrl,skills,location,matchScore,skillMatch,experienceMatch,overallFit,runId,sourcedAt");
            for (Candidate c : candidates) {
                writer.println(csvRow(c));
            }
        } catch (IOException ex) {
            log.error("Error writing CSV export for searchId={}", searchId, ex);
        }
    }

    private String csvRow(Candidate c) {
        return String.join(",",
                q(c.getId()),
                q(c.getName()),
                q(c.getEmail()),
                q(c.getSource() != null ? c.getSource().name() : ""),
                q(c.getSourceUsername()),
                q(c.getProfileUrl()),
                q(c.getSkills() != null ? String.join("|", c.getSkills()) : ""),
                q(c.getLocation()),
                String.valueOf(c.getMatchScore()),
                c.getScoreBreakdown() != null ? String.valueOf(c.getScoreBreakdown().getSkillMatch()) : "",
                c.getScoreBreakdown() != null ? String.valueOf(c.getScoreBreakdown().getExperienceMatch()) : "",
                c.getScoreBreakdown() != null ? String.valueOf(c.getScoreBreakdown().getOverallFit()) : "",
                q(c.getRunId()),
                c.getSourcedAt() != null ? c.getSourcedAt().toString() : ""
        );
    }

    private String q(String value) {
        if (value == null) return "";
        return "\"" + value.replace("\"", "\"\"") + "\"";
    }
}
