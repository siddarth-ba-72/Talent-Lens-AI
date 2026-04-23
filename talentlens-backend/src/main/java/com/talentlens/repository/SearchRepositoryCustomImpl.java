package com.talentlens.repository;

import com.talentlens.model.Search;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.data.mongodb.core.query.Update;
import org.springframework.util.StringUtils;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

public class SearchRepositoryCustomImpl implements SearchRepositoryCustom {

    private final MongoTemplate mongoTemplate;

    public SearchRepositoryCustomImpl(MongoTemplate mongoTemplate) {
        this.mongoTemplate = mongoTemplate;
    }

    @Override
    public Page<Search> findWithFilters(String userId, boolean isHiringManager, SearchFilterParams params, Pageable pageable) {
        List<Criteria> criteriaList = new ArrayList<>();

        if (isHiringManager) {
            criteriaList.add(Criteria.where("sharedWith").in(userId));
        } else {
            criteriaList.add(Criteria.where("userId").is(userId));
        }

        if (StringUtils.hasText(params.getKeyword())) {
            Criteria keywordCriteria = new Criteria().orOperator(
                    Criteria.where("title").regex(params.getKeyword(), "i"),
                    Criteria.where("rawJdText").regex(params.getKeyword(), "i")
            );
            criteriaList.add(keywordCriteria);
        }

        if (StringUtils.hasText(params.getStatus())) {
            criteriaList.add(Criteria.where("sourcingStatus").is(params.getStatus()));
        }

        if (params.getDateFrom() != null) {
            criteriaList.add(Criteria.where("createdAt").gte(params.getDateFrom()));
        }

        if (params.getDateTo() != null) {
            criteriaList.add(Criteria.where("createdAt").lte(params.getDateTo()));
        }

        Criteria combined = new Criteria().andOperator(criteriaList.toArray(new Criteria[0]));
        Query query = new Query(combined).with(pageable);
        Query countQuery = new Query(combined);

        List<Search> results = mongoTemplate.find(query, Search.class);
        long total = mongoTemplate.count(countQuery, Search.class);

        return new PageImpl<>(results, pageable, total);
    }

    @Override
    public void addSharedUserAtomically(String searchId, String userId) {
        Query query = new Query(Criteria.where("_id").is(searchId));
        Update update = new Update()
                .addToSet("sharedWith", userId)
                .set("updatedAt", Instant.now());
        mongoTemplate.updateFirst(query, update, Search.class);
    }
}
