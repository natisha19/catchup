// src/tests/ThemeProvider.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import { ThemeProvider, useTheme } from "../app/providers/ThemeProvider";

function Harness() {
  const { theme, toggle } = useTheme();
  return (
    <div>
      <button onClick={toggle}>toggle-theme</button>
      <span>theme:{theme}</span>
      <p>product content is untouched by theming</p>
    </div>
  );
}

const renderPage = () =>
  render(
    <ThemeProvider>
      <Harness />
    </ThemeProvider>,
  );

beforeEach(() => {
  localStorage.clear();
  document.documentElement.classList.remove("dark");
  document.querySelector('meta[name="theme-color"]')?.remove();
});

describe("ThemeProvider", () => {
  it("defaults to light (system pref is light) and renders children normally", () => {
    renderPage();
    expect(screen.getByText("product content is untouched by theming")).toBeInTheDocument();
    expect(screen.getByText("theme:light")).toBeInTheDocument();
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("toggles to dark, persists the choice, and re-applies it on remount", async () => {
    const user = userEvent.setup();
    const view = renderPage();
    await user.click(screen.getByRole("button", { name: "toggle-theme" }));
    expect(screen.getByText("theme:dark")).toBeInTheDocument();
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(localStorage.getItem("catchup-theme")).toBe("dark");
    // The persisted choice survives a remount (fresh provider instance).
    view.unmount();
    renderPage();
    expect(screen.getByText("theme:dark")).toBeInTheDocument();
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("toggles back to light and clears the stored dark choice", async () => {
    const user = userEvent.setup();
    renderPage();
    const toggle = screen.getByRole("button", { name: "toggle-theme" });
    await user.click(toggle);
    await user.click(toggle);
    expect(screen.getByText("theme:light")).toBeInTheDocument();
    expect(localStorage.getItem("catchup-theme")).toBe("light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });
});