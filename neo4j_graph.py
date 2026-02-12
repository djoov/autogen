"""
neo4j_graph.py - Knowledge Graph Module dengan Neo4j
=====================================================
Module untuk menyimpan dan query knowledge graph (entitas & relasi).
Terintegrasi dengan LLM untuk ekstraksi entitas otomatis.
"""
from neo4j import GraphDatabase
import json
import re
from datetime import datetime
from pathlib import Path
import requests

from config import (
    NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD,
    OLLAMA_API_URL, OLLAMA_MODEL, CODING_OUTPUT_DIR
)

# --- NEO4J CONNECTION ---

class Neo4jGraph:
    """Wrapper untuk operasi Neo4j."""
    
    def __init__(self):
        self.driver = None
        self.connected = False
    
    def connect(self) -> bool:
        """Connect ke Neo4j database."""
        try:
            self.driver = GraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USER, NEO4J_PASSWORD)
            )
            # Test connection
            self.driver.verify_connectivity()
            self.connected = True
            print(f">>> [NEO4J] Connected to {NEO4J_URI}")
            return True
        except Exception as e:
            print(f">>> [NEO4J] Connection failed: {e}")
            self.connected = False
            return False
    
    def close(self):
        """Close connection."""
        if self.driver:
            self.driver.close()
            self.connected = False
    
    def run_query(self, query: str, parameters: dict = None) -> list:
        """Run Cypher query and return results."""
        if not self.connected:
            if not self.connect():
                return []
        
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters or {})
                return [record.data() for record in result]
        except Exception as e:
            print(f">>> [NEO4J] Query error: {e}")
            return []
    
    # --- ENTITY OPERATIONS ---
    
    def save_entity(self, entity_type: str, name: str, properties: dict = None) -> bool:
        """Simpan entitas ke graph."""
        props = properties or {}
        props['name'] = name
        props['created_at'] = datetime.now().isoformat()
        
        # Build property string
        prop_str = ", ".join([f"{k}: ${k}" for k in props.keys()])
        
        query = f"MERGE (n:{entity_type} {{name: $name}}) SET n += {{{prop_str}}} RETURN n"
        result = self.run_query(query, props)
        return len(result) > 0
    
    def save_relationship(self, from_name: str, from_type: str, 
                         rel_type: str, to_name: str, to_type: str,
                         properties: dict = None) -> bool:
        """Simpan relasi antar entitas."""
        props = properties or {}
        
        query = f"""
        MERGE (a:{from_type} {{name: $from_name}})
        MERGE (b:{to_type} {{name: $to_name}})
        MERGE (a)-[r:{rel_type}]->(b)
        SET r += $props
        RETURN a, r, b
        """
        result = self.run_query(query, {
            'from_name': from_name,
            'to_name': to_name,
            'props': props
        })
        return len(result) > 0
    
    def query_entity(self, name: str) -> list:
        """Cari entitas dan relasinya."""
        query = """
        MATCH (n {name: $name})
        OPTIONAL MATCH (n)-[r]->(m)
        RETURN n, type(r) as rel_type, m
        """
        return self.run_query(query, {'name': name})
    
    def query_relationships(self, entity_name: str) -> str:
        """Query semua relasi terkait entitas."""
        query = """
        MATCH (n {name: $name})-[r]-(m)
        RETURN n.name as source, type(r) as relationship, m.name as target, labels(m) as target_type
        """
        results = self.run_query(query, {'name': entity_name})
        
        if not results:
            return f"Tidak ditemukan relasi untuk '{entity_name}'"
        
        output = f"Relasi untuk '{entity_name}':\n"
        for r in results:
            output += f"  - {r['source']} --[{r['relationship']}]--> {r['target']} ({r['target_type'][0] if r['target_type'] else 'Unknown'})\n"
        return output
    
    def get_graph_summary(self) -> str:
        """Dapatkan ringkasan graph."""
        # Count nodes by type
        node_query = """
        MATCH (n)
        RETURN labels(n)[0] as type, count(n) as count
        ORDER BY count DESC
        """
        nodes = self.run_query(node_query)
        
        # Count relationships
        rel_query = """
        MATCH ()-[r]->()
        RETURN type(r) as type, count(r) as count
        ORDER BY count DESC
        """
        rels = self.run_query(rel_query)
        
        output = "=== KNOWLEDGE GRAPH SUMMARY ===\n\n"
        
        if nodes:
            output += "Entities:\n"
            for n in nodes:
                output += f"  - {n['type']}: {n['count']}\n"
        else:
            output += "Entities: (kosong)\n"
        
        output += "\n"
        
        if rels:
            output += "Relationships:\n"
            for r in rels:
                output += f"  - {r['type']}: {r['count']}\n"
        else:
            output += "Relationships: (kosong)\n"
        
        return output
    
    def search_graph(self, query_text: str) -> str:
        """Cari di graph berdasarkan teks."""
        # Search entities by name (case insensitive)
        query = """
        MATCH (n)
        WHERE toLower(n.name) CONTAINS toLower($query)
        OPTIONAL MATCH (n)-[r]-(m)
        RETURN DISTINCT n.name as entity, labels(n)[0] as type, 
               collect(DISTINCT {rel: type(r), target: m.name}) as relationships
        LIMIT 10
        """
        results = self.run_query(query, {'query': query_text})
        
        if not results:
            return ""
        
        output = "KONTEKS DARI KNOWLEDGE GRAPH:\n"
        for r in results:
            output += f"\n[{r['type']}] {r['entity']}\n"
            if r['relationships']:
                for rel in r['relationships']:
                    if rel['rel'] and rel['target']:
                        output += f"  → {rel['rel']}: {rel['target']}\n"
        
        return output
    
    # --- EXPORT/IMPORT ---
    
    def export_graph(self, filename: str = None) -> str:
        """Export graph ke JSON."""
        if not filename:
            filename = f"knowledge_graph_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        if not filename.endswith('.json'):
            filename += '.json'
        
        export_path = CODING_OUTPUT_DIR / filename
        
        # Get all nodes
        nodes_query = """
        MATCH (n)
        RETURN id(n) as id, labels(n) as labels, properties(n) as props
        """
        nodes = self.run_query(nodes_query)
        
        # Get all relationships
        rels_query = """
        MATCH (a)-[r]->(b)
        RETURN id(a) as from_id, type(r) as type, id(b) as to_id, properties(r) as props
        """
        rels = self.run_query(rels_query)
        
        export_data = {
            "exported_at": datetime.now().isoformat(),
            "nodes": nodes,
            "relationships": rels
        }
        
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
            
            size_kb = export_path.stat().st_size / 1024
            return f"[OK] Graph berhasil diekspor!\nFile: {export_path}\nNodes: {len(nodes)}\nRelationships: {len(rels)}\nUkuran: {size_kb:.2f} KB"
        except Exception as e:
            return f"[ERROR] Gagal ekspor graph: {e}"
    
    def import_graph(self, filepath: str) -> str:
        """Import graph dari JSON."""
        json_path = Path(filepath)
        if not json_path.exists():
            json_path = CODING_OUTPUT_DIR / filepath
            if not json_path.exists():
                return f"[ERROR] File tidak ditemukan: {filepath}"
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            nodes_imported = 0
            rels_imported = 0
            
            # Import nodes
            for node in data.get('nodes', []):
                labels = node.get('labels', ['Entity'])
                props = node.get('props', {})
                
                if labels and props.get('name'):
                    self.save_entity(labels[0], props['name'], props)
                    nodes_imported += 1
            
            # Import relationships (simplified - by name matching)
            # Note: This is a simplified approach, real import would need ID mapping
            
            return f"[OK] Graph berhasil diimpor!\nNodes: {nodes_imported}"
        except Exception as e:
            return f"[ERROR] Gagal impor graph: {e}"
    
    def clear_graph(self) -> str:
        """Hapus semua data di graph."""
        try:
            self.run_query("MATCH (n) DETACH DELETE n")
            return "[OK] Knowledge graph di-reset."
        except Exception as e:
            return f"[ERROR] Gagal reset graph: {e}"


# --- ENTITY EXTRACTION ---

def extract_entities_with_llm(text: str) -> dict:
    """Ekstrak entitas dari teks menggunakan LLM."""
    
    prompt = f"""Ekstrak entitas dan relasi dari teks berikut. Output dalam format JSON.

TEKS:
{text[:2000]}

OUTPUT FORMAT:
{{
  "entities": [
    {{"type": "Person", "name": "Nama Orang", "properties": {{"role": "CEO"}}}},
    {{"type": "Organization", "name": "Nama Perusahaan", "properties": {{"industry": "Tech"}}}},
    {{"type": "Product", "name": "Nama Produk", "properties": {{}}}}
  ],
  "relationships": [
    {{"from": "Nama Orang", "from_type": "Person", "rel": "WORKS_AT", "to": "Nama Perusahaan", "to_type": "Organization"}},
    {{"from": "Nama Perusahaan", "from_type": "Organization", "rel": "PRODUCES", "to": "Nama Produk", "to_type": "Product"}}
  ]
}}

ENTITY TYPES: Person, Organization, Location, Product, Technology, Event
RELATIONSHIP TYPES: WORKS_AT, LOCATED_IN, PRODUCES, OWNS, PARTNER_WITH, USES, CREATED_BY

Jawab HANYA dengan JSON, tanpa penjelasan tambahan."""

    try:
        response = requests.post(
            f"{OLLAMA_API_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=120
        )
        
        if response.status_code != 200:
            print(f">>> [ENTITY] LLM error: {response.status_code}")
            return {"entities": [], "relationships": []}
        
        answer = response.json().get("response", "")
        
        # Parse JSON from response
        json_match = re.search(r'\{[\s\S]*\}', answer)
        if json_match:
            return json.loads(json_match.group())
        else:
            print(f">>> [ENTITY] No JSON found in response")
            return {"entities": [], "relationships": []}
            
    except json.JSONDecodeError as e:
        print(f">>> [ENTITY] JSON parse error: {e}")
        return {"entities": [], "relationships": []}
    except Exception as e:
        print(f">>> [ENTITY] Error: {e}")
        return {"entities": [], "relationships": []}


def save_entities_to_graph(graph: Neo4jGraph, extracted: dict) -> str:
    """Simpan hasil ekstraksi ke Neo4j."""
    entities_saved = 0
    rels_saved = 0
    
    # Save entities
    for entity in extracted.get('entities', []):
        entity_type = entity.get('type', 'Entity')
        name = entity.get('name', '')
        props = entity.get('properties', {})
        
        if name:
            if graph.save_entity(entity_type, name, props):
                entities_saved += 1
    
    # Save relationships
    for rel in extracted.get('relationships', []):
        from_name = rel.get('from', '')
        from_type = rel.get('from_type', 'Entity')
        rel_type = rel.get('rel', 'RELATED_TO')
        to_name = rel.get('to', '')
        to_type = rel.get('to_type', 'Entity')
        
        if from_name and to_name:
            if graph.save_relationship(from_name, from_type, rel_type, to_name, to_type):
                rels_saved += 1
    
    return f"Tersimpan: {entities_saved} entitas, {rels_saved} relasi"


# --- SINGLETON INSTANCE ---
_graph_instance = None

def get_graph() -> Neo4jGraph:
    """Get atau create Neo4j graph instance."""
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = Neo4jGraph()
    return _graph_instance
