# BrewSync Admin Client Project

이 프로젝트는 BrewSync Admin 의 클라이언트 프로젝트입니다. 이 프로젝트는 React와 TypeScript를 사용하여 Vite로 빌드됩니다.

# Tech Stack
 - `React` + `TypeScript` + `Vite`
 - `Mantine` for UI components
   - [@mantine/core](https://mantine.dev/core/package/)
 - `Zustand` for state management
   - [zustand](https://zustand.docs.pmnd.rs/getting-started/introduction)
 - `React Query` for data fetching
   - [@tanstack/react-query](https://tanstack.com/query/latest)
 - `mantine-datatable` for data tables (Temporary use)
   - [mantine-data-table](https://icflorescu.github.io/mantine-datatable/) 

# Conventions

## 레이아웃, 페이지, 컴포넌트 파일 작성 규칙

- 레이아웃은 `src/layouts` 폴더에 작성합니다. `/app/auth` 같은 레이아웃 자체가 바뀌는 경우에만 추가합니다.
- 페이지는 `src/pages` 폴더에 작성합니다. 실제 Route 경로에 맞춰 폴더를 작성하고 파일을 생성합니다.
  - 파일 명은 `<RouteName>Page.tsx` 로 작성합니다.
- 컴포넌트는 `src/components/<ComponentName>` 폴더에 작성합니다.
  - 컴포넌트 폴더는 `index.tsx` 파일을 포함해야 하며, 해당 파일에서 컴포넌트를 export 하여 폴더 구조로 import 할 수 있도록 합니다. 
  - 컴포넌트 스타일은 `src/components/<ComponentName>/<ComponentName>.module.css` 파일로 작성합니다.

## Git

- `main` 브랜치는 항상 배포 가능한 상태를 유지해야 합니다.
- `/dev/<feature-name>` 브랜치로 개발을 진행합니다. (임시 규칙)

# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default tseslint.config([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      ...tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      ...tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      ...tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default tseslint.config([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```
