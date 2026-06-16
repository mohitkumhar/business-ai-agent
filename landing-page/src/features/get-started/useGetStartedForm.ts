import { useEffect, useState } from "react";
import { agentApiBaseUrl, signinUrl, dashboardUrl } from "@/constants";
import { markUserOnboarded, normalizeEmail } from "@/lib/onboardingState";
import type { FormData } from "./types";

const initialFormData: FormData = {
  full_name: "",
  phone: "",
  email: "",
  business_name: "",
  business_category: "",
  city: "",
  employees_range: "",
  monthly_revenue: "",
  business_age: "",
  challenges: [],
  finance_tracking_method: "",
  onboarding_notes: "",
};

export function useGetStartedForm() {
  const [sessionReady, setSessionReady] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<FormData>(initialFormData);

  useEffect(() => {
    const savedUser = localStorage.getItem("profit_pilot_user");
    if (!savedUser) {
      window.location.replace(signinUrl);
      return;
    }
    try {
      const user = JSON.parse(savedUser) as {
        full_name?: string;
        email?: string;
        phone?: string;
      };
      setFormData((prev) => ({
        ...prev,
        full_name: user.full_name || prev.full_name,
        email: user.email || prev.email,
        phone: user.phone || prev.phone,
      }));
    } catch (e) {
      console.error("Failed to parse saved user data", e);
    }
    setSessionReady(true);
  }, []);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleChallengeChange = (challenge: string) => {
    setFormData((prev) => {
      const current = [...prev.challenges];
      if (current.includes(challenge)) {
        return { ...prev, challenges: current.filter((c) => c !== challenge) };
      }
      return { ...prev, challenges: [...current, challenge] };
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    if (formData.challenges.length === 0) {
      setError("Please select at least one challenge under Step 3.");
      setIsSubmitting(false);
      return;
    }

    const emailNorm = normalizeEmail(formData.email);
    if (!emailNorm) {
      setError("A valid work email is required.");
      setIsSubmitting(false);
      return;
    }

    try {
      const response = await fetch(`${agentApiBaseUrl}/api/v1/onboarding`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...formData,
          email: emailNorm,
          biggest_challenge: formData.challenges.join(", "),
        }),
      });

      const result = (await response.json()) as {
        error?: string;
        message?: string;
        is_error?: boolean;
      };

      if (response.ok) {
        markUserOnboarded(emailNorm);
        const userStr = localStorage.getItem("profit_pilot_user") || "{}";
        const user = JSON.parse(userStr) as Record<string, unknown>;
        localStorage.setItem(
          "profit_pilot_user",
          JSON.stringify({
            ...user,
            full_name: formData.full_name,
            email: formData.email.trim(),
          })
        );
        setIsSubmitted(true);
      } else {
        setError(
          result.error || result.message || "Failed to submit form. Please try again."
        );
      }
    } catch (err) {
      setError(`Connection error. Is the backend running at ${agentApiBaseUrl}?`);
      console.error(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return {
    sessionReady,
    isSubmitted,
    isSubmitting,
    error,
    formData,
    handleChange,
    handleChallengeChange,
    handleSubmit,
  };
}