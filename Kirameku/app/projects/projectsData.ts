export interface Project {
  id: string;
  name: string;
  description: string;
  longDescription: string;
  coverImage: string;
  techStack: string[];
  links: {
    github?: string;
    gitee?: string;
    live?: string;
    docs?: string;
  };
  featured?: boolean;
  status: "active" | "archived" | "developing";
  statusLabel: string;
}

// 原来的 3 个演示项目（HAXAtom / StarVid 星河 / hiromu.top）已移除。
// 想加自己的项目，照上面 Project 接口补对象即可，例如：
//   {
//     id: "my-project",
//     name: "我的项目",
//     description: "一句话介绍",
//     longDescription: "详细介绍",
//     coverImage: "/images/projects/my-project.webp",
//     techStack: ["Next.js", "FastAPI"],
//     links: { github: "https://github.com/you/repo" },
//     featured: false,
//     status: "developing",
//     statusLabel: "开发中",
//   },
export const projects: Project[] = [];
