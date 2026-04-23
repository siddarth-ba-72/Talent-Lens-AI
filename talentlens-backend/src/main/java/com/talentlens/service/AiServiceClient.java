package com.talentlens.service;

import com.talentlens.model.embedded.ParsedJd;
import org.springframework.web.multipart.MultipartFile;

public interface AiServiceClient {
    ParsedJd parseJd(String jdText);
    ParsedJd parseJdFromFile(MultipartFile file);
}
