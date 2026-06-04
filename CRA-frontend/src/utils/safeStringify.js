export function safeStringify(value, spacing = 2) {
  const seen = new WeakSet();
  try {
    return JSON.stringify(
      value,
      (_key, item) => {
        if (item && typeof item === "object") {
          if (seen.has(item)) return "[Circular]";
          seen.add(item);
        }
        return item;
      },
      spacing
    );
  } catch {
    return String(value ?? "");
  }
}
