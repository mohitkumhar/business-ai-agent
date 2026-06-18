import { templateDefinitions } from "./templates.data";
import type { Template } from "./templates.types";

export * from "./templates.types";
export * from "./templates.constants";

export const templates: Template[] = templateDefinitions.map(
  (template, index) => {
    const slug = template.fileName.replace(".json", "");

    return {
      ...template,
      id: `template-${index + 1}`,
      slug,
    };
  },
);

export const getTemplateBySlug = (slug: string) =>
  templates.find((template) => template.slug === slug);