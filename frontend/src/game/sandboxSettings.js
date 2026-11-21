const prefersReducedMotion = typeof window !== "undefined"
    && typeof window.matchMedia === "function"
    && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

export const DEFAULT_SANDBOX_SETTINGS = Object.freeze({
    fontSize: 14,
    wrapLines: true,
    highContrast: false,
    reducedMotion: prefersReducedMotion,
    chatNotifications: true,
});

const storageKey = (userId) => `cyberplatform:sandbox-settings:${userId}`;

export function loadSandboxSettings(userId) {
    try {
        const saved = JSON.parse(localStorage.getItem(storageKey(userId)));
        if (!saved || typeof saved !== "object") return { ...DEFAULT_SANDBOX_SETTINGS };
        return {
            fontSize: [12, 14, 16, 18, 20].includes(saved.fontSize)
                ? saved.fontSize : DEFAULT_SANDBOX_SETTINGS.fontSize,
            wrapLines: typeof saved.wrapLines === "boolean"
                ? saved.wrapLines : DEFAULT_SANDBOX_SETTINGS.wrapLines,
            highContrast: typeof saved.highContrast === "boolean"
                ? saved.highContrast : DEFAULT_SANDBOX_SETTINGS.highContrast,
            reducedMotion: typeof saved.reducedMotion === "boolean"
                ? saved.reducedMotion : DEFAULT_SANDBOX_SETTINGS.reducedMotion,
            chatNotifications: typeof saved.chatNotifications === "boolean"
                ? saved.chatNotifications : DEFAULT_SANDBOX_SETTINGS.chatNotifications,
        };
    } catch {
        return { ...DEFAULT_SANDBOX_SETTINGS };
    }
}

export function saveSandboxSettings(userId, settings) {
    try {
        localStorage.setItem(storageKey(userId), JSON.stringify(settings));
    } catch {
        // The controls still work for this visit if browser storage is unavailable.
    }
}
