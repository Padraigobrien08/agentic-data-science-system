import { fireEvent, render, screen } from "@testing-library/react";
import { beforeAll, describe, expect, it, vi } from "vitest";

import { CommandPalette, type PaletteCommand } from "@/components/chat-shell/command-palette";

// jsdom does not implement the native dialog methods; stub them so the component's
// open/close effects run the same way they do in a browser.
beforeAll(() => {
  if (!HTMLDialogElement.prototype.showModal) {
    HTMLDialogElement.prototype.showModal = function showModal(this: HTMLDialogElement) {
      this.open = true;
    };
  }
  if (!HTMLDialogElement.prototype.close) {
    HTMLDialogElement.prototype.close = function close(this: HTMLDialogElement) {
      this.open = false;
      this.dispatchEvent(new Event("close"));
    };
  }
});

function buildCommands(run = vi.fn(), disabledRun = vi.fn()): PaletteCommand[] {
  return [
    { id: "a", label: "New chat", hint: "⌘⇧O", group: "Actions", disabled: true, run: disabledRun },
    { id: "b", label: "Edit scope", group: "Actions", run },
    { id: "c", label: "Margin review", hint: "AAPL, MSFT", group: "Chats", run },
    { id: "d", label: "Peer comparison", hint: "AAPL, MSFT", group: "Starter prompts", run },
  ];
}

describe("CommandPalette", () => {
  it("renders grouped commands with their hints when open", () => {
    render(<CommandPalette open onOpenChange={() => {}} commands={buildCommands()} />);

    expect(screen.getByText("Actions")).toBeTruthy();
    expect(screen.getByText("Chats")).toBeTruthy();
    expect(screen.getByText("Starter prompts")).toBeTruthy();
    expect(screen.getByText("New chat")).toBeTruthy();
    expect(screen.getByText("⌘⇧O")).toBeTruthy();
  });

  it("filters across label, group, and hint", () => {
    render(<CommandPalette open onOpenChange={() => {}} commands={buildCommands()} />);
    const input = screen.getByRole("combobox");

    fireEvent.change(input, { target: { value: "margin" } });
    expect(screen.getByText("Margin review")).toBeTruthy();
    expect(screen.queryByText("Edit scope")).toBeNull();

    // hint match
    fireEvent.change(input, { target: { value: "NVDA" } });
    expect(screen.getByText(/Nothing matches/)).toBeTruthy();
  });

  it("runs the highlighted command on Enter and closes", () => {
    const run = vi.fn();
    const onOpenChange = vi.fn();
    // First row is disabled, so move down to the second before selecting.
    render(<CommandPalette open onOpenChange={onOpenChange} commands={buildCommands(run)} />);

    const input = screen.getByRole("combobox");
    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "Enter" });

    expect(run).toHaveBeenCalledTimes(1);
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("does not run a disabled command", () => {
    const disabledRun = vi.fn();
    render(
      <CommandPalette open onOpenChange={() => {}} commands={buildCommands(vi.fn(), disabledRun)} />,
    );

    // The disabled "New chat" row is active by default at index 0.
    fireEvent.keyDown(screen.getByRole("combobox"), { key: "Enter" });
    expect(disabledRun).not.toHaveBeenCalled();
  });

  it("exposes the active row through aria-activedescendant for screen readers", () => {
    render(<CommandPalette open onOpenChange={() => {}} commands={buildCommands()} />);
    const input = screen.getByRole("combobox");

    expect(input.getAttribute("aria-activedescendant")).toBe("command-palette-option-0");
    fireEvent.keyDown(input, { key: "ArrowDown" });
    expect(input.getAttribute("aria-activedescendant")).toBe("command-palette-option-1");

    const options = screen.getAllByRole("option");
    expect(options[1]?.getAttribute("aria-selected")).toBe("true");
    expect(options[0]?.getAttribute("aria-selected")).toBe("false");
  });

  it("wraps around when arrowing past either end", () => {
    render(<CommandPalette open onOpenChange={() => {}} commands={buildCommands()} />);
    const input = screen.getByRole("combobox");

    // Up from the first row wraps to the last of four.
    fireEvent.keyDown(input, { key: "ArrowUp" });
    expect(input.getAttribute("aria-activedescendant")).toBe("command-palette-option-3");
    fireEvent.keyDown(input, { key: "ArrowDown" });
    expect(input.getAttribute("aria-activedescendant")).toBe("command-palette-option-0");
  });
});
