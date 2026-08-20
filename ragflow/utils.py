def print_answer(result):
    print("\n" + "=" * 60)
    print(f"问题:{result.question}")
    print("-" * 60)
    print(result.answer)
    print("-" * 60)
    if result.citations:
        print("引用证据:")
        for index, hit in enumerate(result.citations, start=1):
            snippet = hit.content.replace("\n", " ")
            if len(snippet) > 120:
                snippet = snippet[:120] + "..."
            print(f"  [{index}] {hit.source} score={hit.score:.4f}")
            print(f"      {snippet}")
    else:
        print("引用证据：（无）")
