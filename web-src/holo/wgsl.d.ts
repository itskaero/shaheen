// esbuild's text loader turns `import shader from './x.wgsl'` into a string.
declare module '*.wgsl' {
  const source: string;
  export default source;
}
