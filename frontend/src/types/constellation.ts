export interface ConstellationRelated {
  repo_id: string
  owner: string
  name: string
  run_id: string
  ref_type: 'readme_link' | 'dep_match' | 'same_org_pattern'
  evidence: string
}

export interface ConstellationData {
  related: ConstellationRelated[]
}
