package com.talentlens.service.impl;

import com.talentlens.model.embedded.ParsedJd;
import com.talentlens.service.AiServiceClient;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.annotation.Primary;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

@Service
@Profile("dev-stub")
@Primary
@Slf4j
public class StubAiServiceClient implements AiServiceClient {

    @Override
    public ParsedJd parseJd(String jdText) {
        log.info("[STUB] Returning hardcoded ParsedJd for text input");
        return buildStubResponse();
    }

    @Override
    public ParsedJd parseJdFromFile(MultipartFile file) {
        log.info("[STUB] Returning hardcoded ParsedJd for file: {}", file.getOriginalFilename());
        return buildStubResponse();
    }

    private ParsedJd buildStubResponse() {
        return ParsedJd.builder()
                .skills(List.of("Java", "Spring Boot", "REST APIs", "Microservices"))
                .responsibilities(List.of("Design and build scalable backend systems", "Collaborate with cross-functional teams"))
                .experienceLevel("Senior (5-8 years)")
                .qualifications(List.of("B.S. in Computer Science or equivalent"))
                .technologies(List.of("Java 17", "Spring Boot 3", "Docker", "Kubernetes", "MongoDB"))
                .domain("Backend Engineering")
                .summary("Senior Java Developer for a cloud-native platform, building scalable microservices")
                .build();
    }
}
