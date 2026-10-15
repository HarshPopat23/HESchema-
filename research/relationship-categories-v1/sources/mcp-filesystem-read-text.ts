const ReadTextFileArgsSchema = z.object({
  path: z.string(),
  tail: z
    .number()
    .optional()
    .describe("If provided, returns only the last N lines of the file"),
  head: z
    .number()
    .optional()
    .describe("If provided, returns only the first N lines of the file"),
});


// --- Separate source excerpt ---

    if (args.head && args.tail) {
      throw new Error(
        "Cannot specify both head and tail parameters simultaneously",
      );
    }

    let content: string;
