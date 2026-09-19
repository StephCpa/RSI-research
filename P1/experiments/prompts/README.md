# Audit prompt files

Before the pilot, add three frozen prompt templates here:

- `identity.txt`
- `order_swap.txt`
- `negation.txt`

The order-swap prompt must preserve the semantic question while reversing the
presentation order of the explicit verdict options. The negation prompt must
ask the complementary correctness question and have a declared sign relation.

Do not place hidden-test outcomes or hidden-test content in any prompt.
