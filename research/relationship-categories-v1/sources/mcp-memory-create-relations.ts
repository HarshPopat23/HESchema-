  async createRelations(relations: Relation[]): Promise<Relation[]> {
    return this.withLock(async () => {
      const { graph, unreadable } = await this.loadGraphWithUnreadable();
      const entityNames = new Set(graph.entities.map((e) => e.name));

      relations.forEach((r) => {
        if (!entityNames.has(r.from)) {
          throw new Error(`Entity with name ${r.from} not found`);
        }
        if (!entityNames.has(r.to)) {
          throw new Error(`Entity with name ${r.to} not found`);
        }
      });

      const isSameRelation = (a: Relation, b: Relation) =>
        a.from === b.from && a.to === b.to && a.relationType === b.relationType;
      const newRelations = relations.filter(
        (r, index) =>
          !graph.relations.some((existingRelation) =>
            isSameRelation(existingRelation, r),
          ) &&
          // Also skip duplicates appearing earlier in this same batch
          !relations
            .slice(0, index)
            .some((earlier) => isSameRelation(earlier, r)),
      );
      graph.relations.push(...newRelations);
      await this.saveGraph(graph, unreadable);
      return newRelations;
    });
  }


// --- Separate source excerpt ---

const RelationSchema = z.object({
  from: z.string().describe("The name of the entity where the relation starts"),
  to: z.string().describe("The name of the entity where the relation ends"),
  relationType: z.string().describe("The type of the relation"),
});


// --- Separate source excerpt ---

  // Register create_relations tool
  server.registerTool(
    "create_relations",
    {
      title: "Create Relations",
      description:
        "Create multiple new relations between entities in the knowledge graph. Relations should be in active voice",
      inputSchema: {
        relations: z.array(RelationSchema),
      },
      outputSchema: {
        relations: z.array(RelationSchema),
      },
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: false,
        openWorldHint: false,
      },
    },
    async ({ relations }) => {
      const result = await knowledgeGraphManager.createRelations(relations);
      notifyGraphUpdated();
      return {
        content: [
          { type: "text" as const, text: JSON.stringify(result, null, 2) },
        ],
        structuredContent: { relations: result },
      };
    },
  );
