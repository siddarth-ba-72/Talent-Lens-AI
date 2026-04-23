package com.talentlens.service.impl;

import com.talentlens.exception.AiServiceException;
import com.talentlens.model.embedded.ParsedJd;
import com.talentlens.service.AiServiceClient;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.MediaType;
import org.springframework.http.client.MultipartBodyBuilder;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.reactive.function.BodyInserters;
import org.springframework.web.reactive.function.client.WebClient;

import java.io.IOException;
import java.time.Duration;
import java.util.Map;

@Service
@RequiredArgsConstructor
@Slf4j
public class AiServiceClientImpl implements AiServiceClient {

    private final WebClient aiWebClient;

    @Value("${app.ai-service.timeout-seconds}")
    private long timeoutSeconds;

    @Override
    public ParsedJd parseJd(String jdText) {
        log.info("Calling AI service to parse JD text");
        return aiWebClient.post()
                .uri("/ai/parse-jd")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(Map.of("jdText", jdText))
                .retrieve()
                .onStatus(HttpStatusCode::isError, response ->
                        response.bodyToMono(String.class)
                                .map(body -> new AiServiceException("AI service returned error: " + body))
                )
                .bodyToMono(ParsedJd.class)
                .timeout(Duration.ofSeconds(timeoutSeconds))
                .doOnError(ex -> !(ex instanceof AiServiceException),
                        ex -> log.error("AI service call failed", ex))
                .onErrorMap(ex -> !(ex instanceof AiServiceException),
                        ex -> new AiServiceException("AI service is unavailable", ex))
                .block();
    }

    @Override
    public ParsedJd parseJdFromFile(MultipartFile file) {
        log.info("Calling AI service to parse JD file: {}", file.getOriginalFilename());
        try {
            byte[] bytes = file.getBytes();
            ByteArrayResource resource = new ByteArrayResource(bytes) {
                @Override
                public String getFilename() {
                    return file.getOriginalFilename();
                }
            };

            MultipartBodyBuilder builder = new MultipartBodyBuilder();
            builder.part("jdFile", resource).contentType(
                    file.getContentType() != null
                            ? MediaType.parseMediaType(file.getContentType())
                            : MediaType.APPLICATION_OCTET_STREAM
            );

            return aiWebClient.post()
                    .uri("/ai/parse-jd-file")
                    .contentType(MediaType.MULTIPART_FORM_DATA)
                    .body(BodyInserters.fromMultipartData(builder.build()))
                    .retrieve()
                    .onStatus(HttpStatusCode::isError, response ->
                            response.bodyToMono(String.class)
                                    .map(body -> new AiServiceException("AI service returned error: " + body))
                    )
                    .bodyToMono(ParsedJd.class)
                    .timeout(Duration.ofSeconds(timeoutSeconds))
                    .doOnError(ex -> !(ex instanceof AiServiceException),
                            ex -> log.error("AI service file parse failed", ex))
                    .onErrorMap(ex -> !(ex instanceof AiServiceException),
                            ex -> new AiServiceException("AI service is unavailable", ex))
                    .block();
        } catch (IOException ex) {
            throw new AiServiceException("Failed to read uploaded file", ex);
        }
    }
}
