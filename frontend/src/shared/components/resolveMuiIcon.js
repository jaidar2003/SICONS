export function resolveMuiIcon(iconModule) {
  return iconModule?.default?.default ?? iconModule?.default ?? iconModule;
}
