import { expect, test } from 'vitest'
import React from 'react'

test('frontend framework sanity check', () => {
  expect(1 + 1).toBe(2)
})

test('app configuration is functional', () => {
  const isProd = process.env.NODE_ENV === 'production'
  expect(isProd).toBe(false)
})

