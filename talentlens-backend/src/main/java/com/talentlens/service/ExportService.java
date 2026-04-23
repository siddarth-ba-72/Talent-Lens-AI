package com.talentlens.service;

import com.talentlens.repository.CandidateFilterParams;
import jakarta.servlet.http.HttpServletResponse;

public interface ExportService {
    void export(String searchId, CandidateFilterParams params, HttpServletResponse response);
    String format();
}
