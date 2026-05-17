import React from "react";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";
import CodeTagIcon from "#/icons/code-tag.svg?react";
import LessonPlanIcon from "#/icons/lesson-plan.svg?react";
import PrStatusIcon from "#/icons/pr-status.svg?react";
import { ContextMenu } from "#/ui/context-menu";
import { ContextMenuListItem } from "../context-menu/context-menu-list-item";
import { ContextMenuIconTextWithDescription } from "../context-menu/context-menu-icon-text-with-description";
import { useClickOutsideElement } from "#/hooks/use-click-outside-element";
import { cn } from "#/utils/utils";

const contextMenuListItemClassName = cn(
  "cursor-pointer p-0 h-auto hover:bg-transparent",
);

interface ChangeAgentContextMenuProps {
  onClose: () => void;
  onCodeClick?: (event: React.MouseEvent<HTMLButtonElement>) => void;
  onPlanClick?: (event: React.MouseEvent<HTMLButtonElement>) => void;
  onReviewClick?: (event: React.MouseEvent<HTMLButtonElement>) => void;
}

export function ChangeAgentContextMenu({
  onClose,
  onCodeClick,
  onPlanClick,
  onReviewClick,
}: ChangeAgentContextMenuProps) {
  const { t } = useTranslation();
  const menuRef = useClickOutsideElement<HTMLUListElement>(onClose);

  const handleCodeClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    event.stopPropagation();
    onCodeClick?.(event);
    onClose();
  };

  const handlePlanClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    event.stopPropagation();
    onPlanClick?.(event);
    onClose();
  };

  const handleReviewClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    event.stopPropagation();
    onReviewClick?.(event);
    onClose();
  };

  return (
    <ContextMenu
      ref={menuRef}
      testId="change-agent-context-menu"
      position="top"
      alignment="left"
      className="min-h-fit mb-2 min-w-[195px] max-w-[195px] gap-0"
    >
      <ContextMenuListItem
        testId="code-option"
        onClick={handleCodeClick}
        className={contextMenuListItemClassName}
      >
        <ContextMenuIconTextWithDescription
          icon={CodeTagIcon}
          title={t(I18nKey.COMMON$CODE)}
          description={t(I18nKey.COMMON$CODE_AGENT_DESCRIPTION)}
        />
      </ContextMenuListItem>
      <ContextMenuListItem
        testId="plan-option"
        onClick={handlePlanClick}
        className={contextMenuListItemClassName}
      >
        <ContextMenuIconTextWithDescription
          icon={LessonPlanIcon}
          title={t(I18nKey.COMMON$PLAN)}
          description={t(I18nKey.COMMON$PLAN_AGENT_DESCRIPTION)}
        />
      </ContextMenuListItem>
      <ContextMenuListItem
        testId="review-option"
        onClick={handleReviewClick}
        className={contextMenuListItemClassName}
      >
        <ContextMenuIconTextWithDescription
          icon={PrStatusIcon}
          title="Review"
          description="Review current implementation and findings"
        />
      </ContextMenuListItem>
    </ContextMenu>
  );
}
