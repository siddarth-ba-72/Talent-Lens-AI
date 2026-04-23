package com.talentlens.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;

@Document(collection = "share_requests")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ShareRequest {

    @Id
    private String id;

    private String searchId;
    private String requesterUserId;
    private String ownerUserId;
    private ShareRequestStatus status;
    private Instant requestedAt;
    private Instant resolvedAt;
    private String resolvedBy;
    private String note;
}