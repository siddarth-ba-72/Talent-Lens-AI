package com.talentlens.model;

import com.talentlens.model.embedded.ParsedJd;
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

@Document(collection = "searches")
@CompoundIndexes({
    @CompoundIndex(def = "{'userId': 1, 'createdAt': -1}")
})
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Search {

    @Id
    private String id;

    private String userId;
    private String title;
    private String rawJdText;
    private String jdFileName;
    private ParsedJd parsedJd;
    private SourcingStatus sourcingStatus;
    private List<String> sourcingPlatforms;
    private int candidateCount;
    private List<String> sharedWith;
    private Instant createdAt;
    private Instant updatedAt;
}
