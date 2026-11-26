import hashlib
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.scheme_data.models import Scheme, SchemeStatus, SchemeEmbedding
from app.services.ai.providers.factory import get_embedding_provider

class RetrievalService:
    def __init__(self, db: Session):
        self.db = db
        self.embedding_provider = get_embedding_provider()

    def generate_content_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def get_scheme_text_representation(self, scheme: Scheme) -> str:
        # Create a rich text representation of the scheme
        parts = [
            f"Scheme Name: {scheme.name}",
            f"Description: {scheme.detailed_description}",
            f"Target Group: {scheme.target_group or 'General'}",
        ]
        
        # Add benefits
        if scheme.benefits:
            parts.append("Benefits:")
            for b in scheme.benefits:
                parts.append(f"- {b.benefit_type}: {b.description} ({b.amount_value or 'N/A'})")
                
        # Add rules explanation (simplified for embedding context)
        if scheme.eligibility_rules:
            parts.append("Eligibility Requirements:")
            for r in scheme.eligibility_rules:
                if r.explanation:
                    parts.append(f"- {r.explanation}")
                else:
                    parts.append(f"- {r.field} {r.operator.value} {r.value}")
                    
        return "\n".join(parts)

    async def sync_scheme_embedding(self, scheme_id: str) -> bool:
        """
        Generates or updates the embedding for a published scheme.
        If it's not published, removes the embedding.
        """
        scheme = self.db.query(Scheme).filter(Scheme.id == scheme_id).first()
        if not scheme:
            return False
            
        existing_emb = self.db.query(SchemeEmbedding).filter(SchemeEmbedding.scheme_id == scheme_id).first()
            
        if scheme.status != SchemeStatus.PUBLISHED:
            # Only published schemes should have embeddings
            if existing_emb:
                self.db.delete(existing_emb)
                self.db.commit()
            return True

        text_rep = self.get_scheme_text_representation(scheme)
        content_hash = self.generate_content_hash(text_rep)
        
        if existing_emb and existing_emb.content_hash == content_hash:
            return True # Up to date
            
        # Generate new embedding
        vector = await self.embedding_provider.generate_embedding(text_rep)
        
        if existing_emb:
            existing_emb.embedding = vector
            existing_emb.content_hash = content_hash
            existing_emb.model_name = self.embedding_provider.model_name
            existing_emb.dimension = self.embedding_provider.dimension
        else:
            new_emb = SchemeEmbedding(
                scheme_id=scheme_id,
                model_name=self.embedding_provider.model_name,
                dimension=self.embedding_provider.dimension,
                content_hash=content_hash,
                embedding=vector
            )
            self.db.add(new_emb)
            
        self.db.commit()
        return True

    async def search_schemes(self, query: str, limit: int = 5) -> List[Scheme]:
        """
        Searches ONLY published schemes using vector similarity.
        """
        query_vector = await self.embedding_provider.generate_embedding(query)
        
        # pgvector cosine distance: embedding.cosine_distance(query_vector)
        # We only consider PUBLISHED schemes (which is already enforced by sync_scheme_embedding, 
        # but we add an explicit JOIN to be 100% sure we don't return stale unpublished schemes).
        
        # SQLite fallback for local testing without pgvector
        if self.db.bind.dialect.name == "sqlite":
            stmt = select(Scheme).where(Scheme.status == SchemeStatus.PUBLISHED)
            schemes = list(self.db.execute(stmt).scalars().all())
            query_tokens = {t.strip(".,?!").lower() for t in query.split() if len(t.strip(".,?!")) > 2}

            def score_scheme(scheme: Scheme) -> int:
                haystack = f"{scheme.name} {scheme.short_description} {scheme.detailed_description} {scheme.target_group or ''}".lower()
                return sum(1 for tok in query_tokens if tok in haystack)

            schemes.sort(key=score_scheme, reverse=True)
            return schemes[:limit]
        else:
            stmt = (
                select(Scheme)
                .join(SchemeEmbedding, Scheme.id == SchemeEmbedding.scheme_id)
                .where(Scheme.status == SchemeStatus.PUBLISHED)
                .order_by(SchemeEmbedding.embedding.cosine_distance(query_vector))
                .limit(limit)
            )
        
        if self.db.bind.dialect.name != "sqlite":
            result = self.db.execute(stmt)
            return list(result.scalars().all())
