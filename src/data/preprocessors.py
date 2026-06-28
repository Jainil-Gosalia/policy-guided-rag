"""
Data preprocessing for Policy-Guided RAG
"""
import json
from typing import Dict, List, Any


class ChunkPreparer:
    """Prepare context and guidance chunks from raw data"""

    @staticmethod
    def prepare_context_chunks(cards: List[Dict]) -> List[Dict]:
        """Prepare context chunks from card data

        Args:
            cards: List of card dicts

        Returns:
            List of context chunk dicts
        """
        context_chunks = []
        for card in cards:
            chunk_text = ChunkPreparer.format_card_chunk(card)
            context_chunks.append({
                'id': f"{card['id']}_main",
                'card_id': card['id'],
                'text': chunk_text,
                'type': 'context'
            })
        return context_chunks

    @staticmethod
    def format_card_chunk(card: Dict) -> str:
        """Format a card into a chunk string

        Args:
            card: Card dict

        Returns:
            Formatted chunk text
        """
        rewards = json.dumps(card.get('rewards', {}))
        benefits = ', '.join(card.get('benefits', []))

        return f"Card: {card['name']}\nAnnual Fee: ${card['annual_fee']}\nRewards: {rewards}\nBenefits: {benefits}"

    @staticmethod
    def prepare_guidance_chunks(guidance: List[Dict]) -> List[Dict]:
        """Prepare guidance chunks from guidance data

        Args:
            guidance: List of guidance rule dicts

        Returns:
            List of guidance chunk dicts
        """
        guidance_chunks = []
        for g in guidance:
            chunk = {
                'id': g['id'],
                'text': g['rule'],
                'type': 'guidance'
            }
            # Carry structured policy fields (when present) into chunk metadata so
            # the PolicyOperator can act on them at retrieval time. ChromaDB
            # metadata must be scalar, so target_cards is stored comma-joined.
            if 'action' in g:
                chunk['action'] = g['action']
            if 'target_cards' in g:
                chunk['target_cards'] = ','.join(g.get('target_cards', []))
            guidance_chunks.append(chunk)
        return guidance_chunks

    @staticmethod
    def prepare_all_chunks(cards: List[Dict], guidance: List[Dict]) -> List[Dict]:
        """Prepare all chunks (context + guidance)

        Args:
            cards: List of card dicts
            guidance: List of guidance rule dicts

        Returns:
            Combined list of all chunks
        """
        context = ChunkPreparer.prepare_context_chunks(cards)
        guidance_chunks = ChunkPreparer.prepare_guidance_chunks(guidance)
        return context + guidance_chunks

    @staticmethod
    def extract_chunk_data(chunks: List[Dict]) -> tuple:
        """Extract texts, ids, types, and metadata from chunks

        Args:
            chunks: List of chunk dicts

        Returns:
            Tuple of (texts, ids, types, metadatas)
        """
        texts = [c['text'] for c in chunks]
        ids = [c['id'] for c in chunks]
        types = [c['type'] for c in chunks]
        metadatas = [
            {k: v for k, v in c.items() if k not in ['text', 'type', 'id']}
            for c in chunks
        ]
        return texts, ids, types, metadatas