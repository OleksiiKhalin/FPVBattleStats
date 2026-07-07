import { spawn } from "node:child_process";

const port = process.env.PORT ?? "4173";
const child = spawn(
  process.platform === "win32" ? "npx.cmd" : "npx",
  ["serve", "-s", "dist", "-l", port],
  { stdio: "inherit" },
);

child.on("exit", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }
  process.exit(code ?? 1);
});
