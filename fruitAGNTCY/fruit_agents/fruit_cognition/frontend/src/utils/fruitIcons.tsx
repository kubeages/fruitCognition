/**
 * Map a fruit_type string to a lucide-react icon component plus a tint
 * color from our palette. Used by /cognition and /decisions to give
 * intents a fruit-shop look at a glance.
 *
 * Falls back to a Sprout icon for unknown fruits so the UI always has
 * a green grocer feel even when the IntentManager couldn't identify
 * the fruit.
 */

import {
  Apple,
  Banana,
  Cherry,
  Citrus,
  Grape,
  Leaf,
  Sprout,
  type LucideIcon,
} from "lucide-react"

export interface FruitIcon {
  Icon: LucideIcon
  color: string // hex string, light enough to use on a tinted card
}

// Picked from the project palette neighborhood + classic fruit colors.
export const FRUIT_ICONS: Record<string, FruitIcon> = {
  mango: { Icon: Citrus, color: "#ff9a52" }, // warm orange (theme secondary)
  apple: { Icon: Apple, color: "#d24b4b" }, // bright red apple
  banana: { Icon: Banana, color: "#e8b400" }, // ripe yellow (theme warning)
  strawberry: { Icon: Cherry, color: "#e84855" }, // red berry
  cherry: { Icon: Cherry, color: "#b3151c" },
  grape: { Icon: Grape, color: "#7c3aed" }, // royal purple
  orange: { Icon: Citrus, color: "#ff7a18" },
  lemon: { Icon: Citrus, color: "#f4d35e" },
  lime: { Icon: Citrus, color: "#7cb342" },
}

const FALLBACK: FruitIcon = { Icon: Sprout, color: "#4cbb6c" } // theme primary green
const LEAF: FruitIcon = { Icon: Leaf, color: "#4cbb6c" }

export const fruitIcon = (fruitType: string | null | undefined): FruitIcon => {
  if (!fruitType) return FALLBACK
  return FRUIT_ICONS[fruitType.toLowerCase()] ?? LEAF
}
