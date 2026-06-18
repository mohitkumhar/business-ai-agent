export type TemplateUseCase =
  | "Lead Generation"
  | "Customer Support"
  | "AI Chat"
  | "Quiz & Survey"
  | "E-commerce"
  | "Lead Magnets"
  | "Onboarding"
  | "Entertainment";

export type TemplateFeature =
  | "AI-powered"
  | "Payment integration"
  | "File upload";

export type TemplateCategory = "marketing" | "product";

export type TemplateHighlight = {
  title: string;
  description: string;
};

export type TemplateDefinition = {
  name: string;
  summary: string;
  description: string;
  emoji: string;
  fileName: string;
  category?: TemplateCategory;
  useCase: TemplateUseCase;
  features: TemplateFeature[];
  highlights: TemplateHighlight[];
  bestFor: string[];
  collects?: string[];
  backgroundColor?: string;
  isComingSoon?: boolean;
  isNew?: boolean;
  updatedAt: string;
};

export type Template = TemplateDefinition & {
  id: string;
  slug: string;
};