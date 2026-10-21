# Confirmation study status

**Live execution is in progress. This is not the final experiment report.**

The frozen pack contains 30 new researcher-adapted public-record tasks across
six projects, covering date ordering, identifier matching and list membership.
The planned comparison is 540 slots: three models, three repeats and FULL versus
COMPACT prompting with the same contract validation and one allowed repair.

The 190 offline controls pass. They are validator evidence, not empirical model
results. Forty-seven focused tests cover source reconstruction, alternative valid
answers, oracle isolation, paired analysis, checkpoint resume and public export.

The first invocation completed 185 slots before its quota retry budget was
exhausted. A slower second invocation reached 198 completed slots before the
execution workspace became unavailable. A third invocation resumes the saved
schedule without changing the cases, model settings, runtime file hashes or
primary scoring. Completed checkpointed slots are not regenerated.

The interruption may have lost responses or usage from up to four in-flight
slots, with at most two calls per slot. The exact number of such calls is unknown.
The final report must retain that limitation even if all scheduled slots finish.

Final exact response content, re-scored judgments, source/project-level results,
failure categories, token usage, timing scopes and session histories will be
published with the completed analysis. No missing result or model improvement is
inferred here. Keep this PR in draft until that evidence is attached or the
remaining provider limitation is explicitly reported.
