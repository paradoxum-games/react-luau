<p align="center">
  <p align="center">
	<img width="124" height="124" src="./assets/logo.svg" alt="Logo">
  </p>
  <h1 align="center"><a href="https://www.react-luau.dev"><b>React Luau</b></a></h1>
  <p align="center">
    A comprehensive, but not exhaustive, translation of ReactJS 17.x into <a href="https://luau.org">Luau</a>.
	<!-- <br> -->
	<!-- Shields -->
	<!-- <a href="https://github.com/roblox/react-lua/blob/main/LICENSE">
      <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License">
    </a>
    <a href="https://github.com/Roblox/roact-alignment/actions/workflows/test.yml">
      <img src="https://github.com/Roblox/roact-alignment/actions/workflows/test.yml/badge.svg?branch=main" alt="Build Status">
    </a>
    <a href="https://coveralls.io/github/Roblox/roact-alignment?branch=master">
      <img src="https://coveralls.io/repos/github/Roblox/roact-alignment/badge.svg?branch=master&t=TvTSze" alt="Coverage Status">
    </a> -->
  </p>
</p>

<div align="center">

[![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)

</div>

React Luau is a declarative library for building user interfaces. It's a highly-tuned translation of ReactJS and currently based on React 17.

> [!NOTE]
> This repository is maintained by Paradoxum Games as an independent downstream fork
> of Roblox React Luau. Upstream projects remain important semantic and historical
> references, but changes here may intentionally diverge to serve this fork.

> [!IMPORTANT]
> The `paradoxum/*` Wally package family is staged and validated in this repository,
> but it has not been published. The existing Rotriever workspace still drives the
> runtime test suite until Wally workspace parity is complete. Do not use the legacy
> `roblox/react` package as if it were this fork. Staged package manifests are private,
> and all Multipack publication destinations are disabled.

* **Declarative:** React makes it easy to create interactive UIs. Design simple views for each state in your application, and React will efficiently update and render just the right components when your data changes. Declarative views make your code more predictable, simpler to understand, and easier to debug.
* **Component-Based:** Build encapsulated components that manage their own state, then compose them to make complex UIs. Since component logic is written in Luau instead of managed with Roblox's Instances, you can easily pass rich data through your code and keep the state out of the data model.
* **Tuned for Roblox:** Luau is not Javascript, so we deviate from ReactJS in certain places for a more ergonomic programming experience in Luau and with Roblox's wider programming model. For example, React Luau introduces Bindings, a form of signals-based state that doesn't re-render, for highly-efficient animations driven by React.

[Learn how to use React Luau in your project](https://www.react-luau.dev/).

<!-- ## Installation

React Luau has been designed for gradual adoption from the start, and **you can use as little or as much React as you need**:

- Use [Quick Start](https://www.react-luau.dev/) to get a taste of React.
- [Add React to an Existing Project](https://www.react-luau.dev/) to use as little or as much React as you need.

## Documentation

You can find the React Luau documentation [on the website](https://www.react-luau.dev/).

Check out the [Getting Started](https://www.react-luau.dev/) page for a quick overview.

The documentation is divided into several sections:

- TODO -->

## Examples

We have several examples [on the website](https://www.react-luau.dev/). Here is the first one to get you started:

```luau
local React = require(Packages.React)
local ReactRoblox = require(Packages.ReactRoblox)

local e = React.createElement

local function HelloMessage(props: {
	name: string,
})
	return e("TextLabel", {
		AnchorPoint = Vector2.new(0.5, 0.5),
		Position = UDim2.fromScale(0.5, 0.5),
		AutomaticSize = Enum.AutomaticSize.XY,
		Text = `Hello, {props.name}!`,
	})
end

local function App()
	return e("ScreenGui", {}, {
		MyMessage = e(HelloMessage, {
			name = "Taylor",
		}),
	})
end

local root = ReactRoblox.createRoot(Instance.new("Folder"))
root:render(ReactRoblox.createPortal(e(App), Players.LocalPlayer.PlayerGui))
```

This example will render "Hello, Taylor!" into a TextLabel on the screen.

## Development

Start with [Maintaining the Paradoxum React Luau fork](./docs/maintainer-workflow.md).
Coding agents automatically receive the repository-specific rules in
[AGENTS.md](./AGENTS.md).

The Wally package set is declared in [wally-package-set.toml](./wally-package-set.toml).
Validate all nine real archives and a clean unpublished consumer without publishing:

```sh
bash bin/ci-wally-packages.sh
```

This gate checks exact package identities and dependencies, archive contents, the
committed consumer lockfile, Wally's `_Index` dependency layout, and a Rojo sourcemap
and build.

`rokit.toml` declares the target public tool pins. During the transition, Rokit 1.2
also discovers the legacy `foreman.toml`, whose private tools prevent a clean
`rokit install`; keep using the existing test bootstrap until the workspace cutover.

## License

React Luau is [MIT licensed](./LICENSE). Go do cool stuff with it!
