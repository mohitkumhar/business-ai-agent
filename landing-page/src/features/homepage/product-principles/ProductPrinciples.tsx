import { buttonVariants } from "@typebot.io/ui/components/Button";
import { ArrowDown01Icon } from "@typebot.io/ui/icons/ArrowDown01Icon";
import { ArrowUp01Icon } from "@typebot.io/ui/icons/ArrowUp01Icon";
import { cn } from "@typebot.io/ui/lib/cn";
import { motion } from "motion/react";
import { useState } from "react";
import threeDButton from "./assets/3d-button.png";

const data = [
  {
    title: "Set Up in Minutes, Not Months",
    content:
      "ProfitPilot comes with pre-built financial templates for Cash Flow, Expense Tracking, and Hiring. Simply connect your data sources (like Google Sheets or Banks), and start getting answers immediately—no coding or complex setup required.",
  },
  {
    title: "Your 24/7 Financial Analyst",
    content:
      "Your advisor never sleeps. Whether it's 2 AM on a Tuesday or a holiday weekend, get instant clarity on your business health. Ask questions like 'How much cash do I have?' or 'Did ad spend go up?' and get an answer in seconds.",
  },
  {
    title: "Simple Answers to Complex Questions",
    content:
      "We strip away the confusing accounting jargon. Instead of staring at complex spreadsheets, you get clear, actionable advice in plain English. It's like having a friendly CFO explain your numbers to you. ",
  },
  {
    title: "Enterprise-Grade Security",
    content:
      "Your financial data is sensitive. That's why ProfitPilot is built with bank-level security. We use industry-standard encryption and privacy controls to ensure your numbers stay private and protected. No data is sold, ever.",
  },
  {
    title: "Smarter Every Day",
    content:
      "As your business grows, so does your AI. It learns from your past decisions and seasonal trends to provide increasingly accurate forecasts, helping you spot opportunities before your competitors do.",
  },
];

export const ProductPrinciples = () => {
  const [openedIndex, setOpenedIndex] = useState<number | null>(0);

  const toggleIndex = (index: number) => {
    if (openedIndex === index) return;
    setOpenedIndex(index);
  };

  return (
    <div className="flex flex-col gap-8 max-w-7xl w-full">
      <h2>Built to Make Your Business Life Easier</h2>
      <div className="flex md:bg-white rounded-2xl gap-4 p-2 items-start border">
        <div className="flex flex-col gap-2 md:gap-0 md:pl-4 w-full">
          {data.map(({ title, content }, index) => (
            <Principle
              key={title}
              title={title}
              content={content}
              isOpened={index === openedIndex}
              isLastItem={index === data.length - 1}
              onClick={() => toggleIndex(index)}
            />
          ))}
        </div>
        <img
          src={threeDButton}
          alt="3D illustration featuring the ProfitPilot logo"
          className="max-w-lg md:block hidden"
        />
      </div>
    </div>
  );
};

const Principle = ({
  title,
  content,
  isOpened,
  isLastItem,
  onClick,
}: {
  title: string;
  content: string;
  isOpened: boolean;
  isLastItem: boolean;
  onClick: () => void;
}) => {
  return (
    <details
      className="rounded-xl md:rounded-none md:px-0 bg-white border md:border-0 border-border cursor-pointer"
      open={isOpened}
    >
      <summary
        className="px-4 py-4 md:py-2 font-display font-medium text-2xl flex flex-col gap-3 list-none"
        onClick={(e) => {
          e.preventDefault();
          onClick();
        }}
      >
        <div className="flex justify-between">
          {title}
          <span
            className={cn(
              buttonVariants({ variant: "secondary", size: "icon" }),
              "shrink-0 [&_svg]:size-6",
            )}
          >
            {isOpened ? (
              <ArrowUp01Icon className="size-8" />
            ) : (
              <ArrowDown01Icon />
            )}
          </span>
        </div>

        {isLastItem ? null : <hr className="hidden md:block" />}
      </summary>
      <motion.div
        initial={{ height: 0, opacity: 0 }}
        animate={{
          height: isOpened ? "auto" : 0,
          opacity: isOpened ? 1 : 0,
        }}
        transition={{ duration: 0.4, type: "spring", bounce: 0.15 }}
      >
        <hr className="mb-4 md:hidden mx-4 border-border" />
        <p className="pb-4 mx-4">{content}</p>
      </motion.div>
    </details>
  );
};
