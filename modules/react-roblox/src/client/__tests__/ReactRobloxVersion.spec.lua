--[[
	* Copyright (c) Roblox Corporation. All rights reserved.
	* Licensed under the MIT License (the "License");
	* you may not use this file except in compliance with the License.
	* You may obtain a copy of the License at
	*
	*     https://opensource.org/licenses/MIT
	*
	* Unless required by applicable law or agreed to in writing, software
	* distributed under the License is distributed on an "AS IS" BASIS,
	* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
	* See the License for the specific language governing permissions and
	* limitations under the License.
]]

local Packages = script.Parent.Parent.Parent.Parent

local JestGlobals = require(Packages.Dev.JestGlobals)
local jestExpect = JestGlobals.expect
local it = JestGlobals.it

it("reports the downstream package family version", function()
	local Shared = require(Packages.Shared)
	local React = require(Packages.React)
	local ReactRoblox = require(Packages.ReactRoblox)

	jestExpect(Shared.ReactVersion).toBe("17.3.10")
	jestExpect(React.version).toBe(Shared.ReactVersion)
	jestExpect(ReactRoblox.version).toBe(Shared.ReactVersion)
end)
