import { UnstyledButton } from "@mantine/core";
import type { ComponentPropsWithRef } from "react";

import "./editable-value.css";

type EditableValueProps = ComponentPropsWithRef<"button">;

/**
 * A value that is edited in place: reads as text, with a dashed underline at rest that tells it
 * apart from read-only values. Every screen marks its editable values with this, never its own style.
 */
export function EditableValue({ className, ...props }: EditableValueProps) {
  return (
    <UnstyledButton
      {...props}
      className={className === undefined ? "editable-value" : `editable-value ${className}`}
    />
  );
}
