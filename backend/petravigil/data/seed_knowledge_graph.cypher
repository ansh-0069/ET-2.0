// Phase 2 starter seed for Neo4j. The API currently uses the same JSON data
// through a local graph projection, so the prototype remains runnable offline.
MERGE (jamnagar:Refinery {name: 'Jamnagar'})
SET jamnagar.operator = 'Reliance Industries', jamnagar.capacity_mmtpa = 68.2, jamnagar.complexity_index = 14.0
MERGE (paradip:Refinery {name: 'Paradip'})
SET paradip.operator = 'IndianOil', paradip.capacity_mmtpa = 15.0, paradip.complexity_index = 12.0
MERGE (kochi:Refinery {name: 'Kochi'})
SET kochi.operator = 'Bharat Petroleum', kochi.capacity_mmtpa = 15.5, kochi.complexity_index = 9.7
MERGE (hormuz:Chokepoint {name: 'HORMUZ'})
MERGE (wti:CrudeGrade {name: 'WTI Midland'}) SET wti.country = 'United States', wti.api_gravity = 41.5, wti.sulfur_pct = 0.3
MERGE (liza:CrudeGrade {name: 'Liza Light'}) SET liza.country = 'Guyana', liza.api_gravity = 32.1, liza.sulfur_pct = 0.5
MERGE (wti)-[:COMPATIBLE_WITH]->(jamnagar)
MERGE (wti)-[:COMPATIBLE_WITH]->(kochi)
MERGE (liza)-[:COMPATIBLE_WITH]->(jamnagar)
MERGE (liza)-[:COMPATIBLE_WITH]->(paradip)
MERGE (gulf:Route {name: 'Persian Gulf -> West India'}) SET gulf.transit_days = 8, gulf.risk_score = 0.78
MERGE (gulf)-[:PASSES_THROUGH]->(hormuz)
