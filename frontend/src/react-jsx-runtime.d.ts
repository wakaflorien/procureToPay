/* eslint-disable */
/// <reference types="react" />

declare module 'react/jsx-runtime' {
  import { ReactElement } from 'react';
  
  export function jsx(
    type: any,
    props: any,
    key?: any
  ): ReactElement;
  
  export function jsxs(
    type: any,
    props: any,
    key?: any
  ): ReactElement;
  
  export const Fragment: React.ComponentType<{ children?: React.ReactNode }>;
}

