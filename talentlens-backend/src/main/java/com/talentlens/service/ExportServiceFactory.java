package com.talentlens.service;

import com.talentlens.exception.InvalidFileException;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

@Component
public class ExportServiceFactory {

    private final Map<String, ExportService> services;

    public ExportServiceFactory(List<ExportService> serviceList) {
        this.services = serviceList.stream()
                .collect(Collectors.toMap(ExportService::format, Function.identity()));
    }

    public ExportService get(String format) {
        ExportService service = services.get(format.toLowerCase());
        if (service == null) {
            throw new InvalidFileException("Unsupported export format: " + format + ". Allowed: csv, json");
        }
        return service;
    }
}
