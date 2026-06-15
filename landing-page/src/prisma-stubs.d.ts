declare module "@prisma/client/default" {
  export interface User { id: string; email: string | null; name?: string | null; image?: string | null; }
  export interface Workspace { id: string; name: string; plan: string; }
  export interface MemberInWorkspace { id?: string; userId: string; workspaceId: string; role: string; }
  export interface WorkspaceInvitation { id: string; email: string; workspaceId: string; }
  export interface CollaboratorsOnTypebots { type: any; userId: string; typebotId: string; createdAt: Date; updatedAt: Date; }
  export interface CustomDomain { name: string; workspaceId: string; createdAt: Date; }
  export interface DashboardFolder { workspaceId: string; name: string; createdAt: Date; updatedAt: Date; parentId?: string | null; parentFolderId?: string | null; }
}

declare module "@prisma/client" {
  export interface User { id: string; email: string | null; name?: string | null; image?: string | null; }
  export interface Workspace { id: string; name: string; plan: string; }
  export interface MemberInWorkspace { id?: string; userId: string; workspaceId: string; role: string; }
  export interface WorkspaceInvitation { id: string; email: string; workspaceId: string; }
  export interface CollaboratorsOnTypebots { type: any; userId: string; typebotId: string; createdAt: Date; updatedAt: Date; }
  export interface CustomDomain { name: string; workspaceId: string; createdAt: Date; }
  export interface DashboardFolder { workspaceId: string; name: string; createdAt: Date; updatedAt: Date; parentId?: string | null; parentFolderId?: string | null; }

  export type ChatProvider = "OPENAI" | "ANTHROPIC" | "MISTRAL";
  export type CollaborationType = "EDIT" | "READ";
  export type GraphNavigation = "FREE" | "TRACKPAD";
  export type Plan = "FREE" | "STARTER" | "PRO" | "UNLIMITED" | "LIFETIME" | "OFFERED" | "CUSTOM" | "ENTERPRISE";
  export type WorkspaceRole = "ADMIN" | "MEMBER" | "GUEST";
  
  export const ChatProvider: any;
  export const CollaborationType: any;
  export const GraphNavigation: { FREE: "FREE"; TRACKPAD: "TRACKPAD" };
  export const Plan: { FREE: "FREE"; STARTER: "STARTER"; PRO: "PRO"; UNLIMITED: "UNLIMITED"; LIFETIME: "LIFETIME"; OFFERED: "OFFERED"; CUSTOM: "CUSTOM"; ENTERPRISE: "ENTERPRISE" };
  export const WorkspaceRole: any;

  export namespace Prisma {
    export const JsonNull: any;
    export const DbNull: any;
    export class PrismaClientKnownRequestError extends Error {
      code?: string;
    }
  }
  
  export class PrismaClient {
    constructor(options?: any);
    $extends(args?: any): any;
  }
}

declare module "@typebot.io/prisma" {
  export const prisma: any;
  export const publicTypebot: any;
  export const result: any;
  export const workspace: any;
  export default prisma;
}

declare module "@typebot.io/prisma/effect" {
  export const PrismaClientService: any;
  export const PrismaService: any;
  export type PrismaService = any;
}
